from random import randint
import cv2
import numpy as np
import orient_calc as oc


# function to get the output layer names 
# in the architecture
def get_output_layers(net):
    
    layer_names = net.getLayerNames()
    
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    return output_layers

# function to draw bounding box on the detected object with class name
def draw_bounding_box(img, obj):

    label = obj.Label
    confidence = 'conf- ' + str(obj.confidence)
    ip_ang = 'ip-ang: ' + str(obj.inplane_rot)
    op_ang = 'op-ang(x,y): ' + str(obj.op_rot)
    scale = 'scale: ' + str(obj.scale)


    color = (66, 80, 244)

    x = round(obj.top_left[0])
    y = round(obj.top_left[1])
    obj_width = round(obj.top_left[0] + (obj.dims[0]))
    obj_height = round(obj.top_left[1] + (obj.dims[1]))

    #debug draw circles for gear and db
    if(obj.center_d and obj.center_g):
        x_g = round(obj.center_g[0])
        y_g = round(obj.center_g[1])
        x_d = round(obj.center_d[0])
        y_d = round(obj.center_d[1])
        center_x = round(obj.center[0])
        center_y = round(obj.center[1])


        cv2.circle(img, (x_g,y_g), 5, color, thickness=1, lineType=8, shift=0)
        cv2.circle(img, (x_d,y_d), 5, color, thickness=1, lineType=8, shift=0)

    cv2.rectangle(img, (x,y), (obj_width,obj_height), color, 2)

    cv2.putText(img, label, (x-5,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.25, color, 1)
    cv2.putText(img, confidence, (x-5,y+obj.dims[1]+10), cv2.FONT_HERSHEY_SIMPLEX, 0.25, color, 1)
    cv2.putText(img, ip_ang, (x-5,y+obj.dims[1]+20), cv2.FONT_HERSHEY_SIMPLEX, 0.25, color, 1)
    cv2.putText(img, op_ang, (x-5,y+obj.dims[1]+30), cv2.FONT_HERSHEY_SIMPLEX, 0.25, color, 1)
    cv2.putText(img, scale, (x-5,y+obj.dims[1]+40), cv2.FONT_HERSHEY_SIMPLEX, 0.25, color, 1)
    
def main():

    Width = 512
    Height = 512
    scale = 0.00392
    random_num = randint(10,5000)

    classes_file = '.\production\classes\obj.names'
    weights = '.\production\weights\yolov3-tiny-obj_28900.weights'
    config = '.\production\cfg\yolov3-tiny-obj - copy.cfg'

    z= 0
    cam = cv2.VideoCapture(0)

    # read and resize input image
    # image = cv2.imread(img)
    while(True):
        
        ret,img = cam.read()
        image = cv2.resize(img, (Width,Height))
        img2 = cv2.resize(img, (Width,Height))

        # read class names from text file
        # # classes = None
        # with open(classes_file, 'r') as f:
        #     classes = [line.strip() for line in f.readlines()]

        # generate different colors for different classes 
        # COLORS = np.random.uniform(0, 255, size=(len(classes), 3))

        # read pre-trained model and config file
        net = cv2.dnn.readNetFromDarknet( config, weights)

        # create input blob 
        blob = cv2.dnn.blobFromImage(image, scale, (Width,Height), (0,0,0), True, crop=False)

        # set input blob for the network
        net.setInput(blob)

        # run inference through the network
        # and gather predictions from output layers
        outs = net.forward(get_output_layers(net))

        # initialization
        class_ids = []
        boxes = []
        confidences = []
        objects = []
        gears = []
        dbs = []
        text_boxes = []
        text_boxes_inverted = []
        conf_threshold = 0.5       
        nms_threshold = 0.4

        # for each detetion from each output layer 
        # get the confidence, class id, bounding box params
        # and ignore weak detections (confidence < 0.5)
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    center_x = int(detection[0] * Width)
                    center_y = int(detection[1] * Height)
                    w = int(detection[2] * Width)
                    h = int(detection[3] * Height)
                    x = center_x - w / 2
                    y = center_y - h / 2
                    class_ids.append(class_id)
                    confidences.append(float(confidence))
                    boxes.append([x, y, w, h])


        # apply non-max suppression
        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

        # go through the detections remaining
        # after nms and draw bounding box
        for i in indices:
            i = i[0]
            box = boxes[i]

            if(class_ids[i] == 0):
                new_obj = oc.track_obj()
                new_obj.Label = 'obj: ' + str(i)
                new_obj.top_left = (box[0],box[1])
                new_obj.center =(box[0]+(box[2]/2),box[1]+(box[3]/2))
                new_obj.dims = (box[2],box[3])
                new_obj.confidence = round(confidences[i],2)
                objects.append(new_obj)

            elif(class_ids[i] == 1):
                gears.append(box)

            elif(class_ids[i] == 2):
                dbs.append(box)
        
        for obj in objects:

            for gear in gears:
                if(oc.in_main_obj(obj,gear)):
                    obj.center_g = (gear[0]+(gear[2]/2),gear[1]+(gear[3]/2))
                    obj.dims_g = (gear[2],gear[3])
                    # print("gear added")
                    break

            for db in dbs:
                if(oc.in_main_obj(obj,db)):
                    obj.center_d = (db[0]+(db[2]/2),db[1]+(db[3]/2))
                    obj.dims_d = (db[2],db[3])
                    # print("db added")
                    break

        for obj in objects:

            obj.get_inplane()
            obj.get_scale()
            obj.get_outplane()
            # if(obj.valid()):
            #     text_boxes.append(obj.boxes)
            #     text_boxes.append(obj.db_box)
            #     text_boxes.append(obj.gear_box)
            # if(obj.valid_inverted()):
            #     text_boxes_inverted.append(obj.boxes_inverted)
            #     text_boxes_inverted.append(obj.db_box_inverted)
            #     text_boxes_inverted.append(obj.gear_box_inverted)

            draw_bounding_box(image, obj)
        
        #if the image and detection was valid save them for training
        # if(text_boxes):
        #     file = open('./frames/img_' + str(random_num) + str(z) + '.txt', 'w+')
        #     for item in text_boxes:
        #         file.write("%s\n" % item[0])
        #     file.close()
        #     cv2.imwrite('./frames/img_' + str(random_num) + str(z) + '.jpg',img2)

        # #if the image and detection was valid save them for training
        # if(text_boxes_inverted):
        #     file = open('./frames/img_IN_' + str(random_num) + str(z) + '.txt', 'w+')
        #     for item in text_boxes_inverted:
        #         file.write("%s\n" % item[0])
        #     file.close()
        #     flipped_img = cv2.flip( img, -1 )
        #     cv2.imwrite('./frames/img_IN_' + str(random_num) + str(z) + '.jpg',flipped_img)
        
        # display output image
        image = cv2.resize(image, (1024,1024))
        cv2.imwrite('./samples/capframe_' + str(random_num) + str(z) + '.jpg',image)
        cv2.imshow("object detection", image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        z += 1

    # # wait until any key is pressed
    # cv2.waitKey()
        
    # # save output image to disk
    # cv2.imwrite("object-detection.jpg", image)

    # release resources
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
